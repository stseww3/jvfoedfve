#!/usr/bin/env python3
"""The twelve board views (plan/ART-PLAN.md 4) as a shot list for the master scene.

    boardshots.py             say where the landmarks of the site fall in every view; nothing is written
    boardshots.py --write     write tools/win/shots/obs-board.json, the list kept in the repository
    boardshots.py --check     end with 1 when that file is not what the skeleton gives now
    boardshots.py --out <f>   write the list to another file (the shuttle does, for every trip)

Every position is worked out from build/scenes/obs/common/skeleton.py, so the list moves with the
skeleton: after a change there, --write and commit. Only arithmetic; no scene is built. The
skeleton is the one of this checkout, or of the build/ folder named in the environment variable
C164_BUILD: the render station shoots other checkouts with its own tools (win/shuttle.py), and
the board of a checkout is worked out from that checkout's skeleton.

V1, V2, V5, V6, V7, V8 and V11 are the skeleton's own, LOCKED there. The other five have no place in
the skeleton yet: what stands here for them is the render station's proposal (PROPOSED below), to be
moved on the pictures. A view that gets fixed goes into the skeleton as V<n> = dict(pos=, look_at=)
and is read from there; the proposal here then no longer counts (V5, V6, V7 and V8 have one each).

All twelve are taken in look A (tick 14000). The picture is the game's: 16:9, 77 degrees high (the
camera player flies, which widens the game's 70), as build/render.py and tools/check.py take it.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("C164_BUILD") or os.path.normpath(os.path.join(HERE, "..", "build")))

from scenes.obs.common import skeleton as S  # noqa: E402

FILE = os.path.join(HERE, "win", "shots", "obs-board.json")
TIME = 14000
FOV, ASPECT = 77.0, 16.0 / 9.0
SERVER_SENDS = 160.0        # blocks on the ground within which the server sends display entities
#                             (read from the game's code; tools/check.py reports the same number)

EYE = S.EYE
MAIN_EYE = S.STAND + EYE                    # 8.62, a person on the main floor or on a gallery
TOWER = (S.mid(*S.CLOCK_SHAFT_X), S.mid(*S.CLOCK_SHAFT_Z))      # (13.5, -29.5), the tower's axis
HOUSE = S.POWER_HOUSE["box"]


def _ruled():
    """V1 and V2 as A0 ruled them on 11-14 (group #304): both tilted up to about 22 degrees so that
    the whole comet is in the picture. S2 writes V2 into the skeleton with that ruling, so a
    skeleton without V2 is older than it and still carries the earlier look_at of V1."""
    if hasattr(S, "V2"):
        return S.V1, S.V2
    return dict(pos=S.V1["pos"], look_at=(8, 34, 0.5)), dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5))


V1, V2 = _ruled()

# name, what the plan wants to see, the skeleton's name for it, the render station's proposal
VIEWS = [
    ("v01_arrival", "from the cable station up at the whole observatory", "V1", V1),
    ("v02_axis", "the entrance and the dome head-on from the court's axis", "V2", V2),
    # PROPOSED. Two bays and the corner between the centre block and the south wing, from the court:
    # rough base, string course, fine main storey, a great window, the pilaster's lamp, the downpipe.
    ("v03_facade", "two bays of wall and a lamp, close", "V3", dict(
        pos=(S.WALL_E + 9.5, S.GROUND + EYE, S.pilaster_z(11) + 2.5),
        look_at=(S.WALL_E + 1.5, S.STRING + 0.5, S.pilaster_z(10) + 0.5))),
    # PROPOSED. Ten blocks out, three off the axis: door, fanlight, canopy, both bracket lamps, plate.
    ("v04_entrance", "the iron door, the canopy, the bracket lamps, the name plate", "V4", dict(
        pos=(S.east_wall_x(9) + 10.5, S.GROUND + EYE, S.AXIS_Z + 3.0),
        look_at=(S.east_wall_x(9) + 0.5, 4.5, S.AXIS_Z))),
    # No longer counts: V5 is in the skeleton, 42 blocks from the tower (S2 11-16). The proposal was:
    # from the court, south-east of the tower, looking up its corner: the east and south dials, the
    # time ball on its mast, the aerial across to the radio mast on the right. From there the top,
    # the ball and its pole are behind the cornice (main/tower worked it out from the blocks).
    ("v05_tower", "up the clock tower: the dials, the time ball, the aerial", "V5", dict(
        pos=(TOWER[0] + 15.0, S.GROUND + EYE, TOWER[1] + 15.0),
        look_at=(TOWER[0], S.CLOCK_SHAFT_TOP - 3.0, TOWER[1]))),
    # No longer counts: A0 fixed V6 on the grand stair's south half (#55097), it is in the skeleton.
    # The proposal was: on the lower platform, east of the stair's foot, the north front of the power
    # house, the chimney over it; the pipe bridge is not in that picture.
    ("v06_power", "the power house: chimney, pipe bridge, the glowing windows", "V6", dict(
        pos=(S.GRAND_STAIR["x1"] + 2.5, S.LOWER_GROUND + EYE, S.GRAND_STAIR["z1"] - 5.5),
        look_at=(S.mid(HOUSE[0], HOUSE[2]), S.POWER_HOUSE["base_y"] + S.POWER_HOUSE["wall_h"] - 1.0,
                 S.mid(HOUSE[1], HOUSE[3])))),
    # No longer counts: V7 is in the skeleton. The proposal was: on the south gallery, level with the
    # ring of planets, the orrery in the well, the pier and the mother clock behind it, the floor below.
    ("v07_hall", "the star hall and the orrery", "V7", dict(
        pos=(S.east_wall_x(9) - 3.5, MAIN_EYE, S.STAR_HALL_Z[1] - 0.5),
        look_at=(S.PIER_SHAFT[2] + 1.0, S.STAND - 1.0, S.STAR_HALL_Z[0] + 3.0))),
    # No longer counts: V8 is in the skeleton, the refractor's own station (S2 11-16). The proposal
    # was: on the dome-room floor east of the pier, inside the slit's width and beside the tube, so
    # that the line due west at the comet's height runs out through the slit. From there the tube
    # points at the lens and hides half the slit.
    ("v08_dome_room", "the great refractor, the open slit, the comet beyond it", "V8", dict(
        pos=(S.DOME_AXIS[0] + 8.0, S.ROOF_STAND + EYE, S.DOME_AXIS[1] + 1.5),
        look_at=(S.DOME_AXIS[0] - 10.0, S.ROOF_STAND + 10.0, S.DOME_AXIS[1]))),
    # PROPOSED. South wing, main floor, from the corner by the door down the length of the room.
    ("v09_chart_room", "the star-chart room: shelves, the plate table, the green lamp", "V9", dict(
        pos=(S.ROOM_X[1] - 0.5, MAIN_EYE, S.STAR_HALL_Z[1] + 2.5),
        look_at=(S.ROOM_X[0] + 2.0, S.STAND + 1.0, S.pilaster_z(15) - 5.0))),
    # PROPOSED. North wing, main floor: V9's mirror about the axis.
    ("v10_time_room", "the time room: the whole wall of instruments", "V10", dict(
        pos=(S.ROOM_X[1] - 0.5, MAIN_EYE, 2 * S.AXIS_Z - (S.STAR_HALL_Z[1] + 2.5)),
        look_at=(S.ROOM_X[0] + 2.0, S.STAND + 1.0, 2 * S.AXIS_Z - (S.pilaster_z(15) - 5.0)))),
    ("v11_lookout", "back from the south lookout, three-quarter, the afterglow on the left", "V11", S.V11),
    # PROPOSED. From the south-east, high. Every mass of the site, the radio mast's top and all four
    # corners of the lower platform are at least a tenth of the picture inside its edges, and nothing
    # of the site is further off on the ground than the server sends display entities (153 blocks).
    ("v12_aerial", "the whole site from above", "V12", dict(
        pos=(S.EAST_EDGE_X + 20.0, 90.0, S.Z_SOUTH + 46.0),
        look_at=(S.MERIDIAN_X, S.GROUND, S.AXIS_Z - 5.5))),
]


def views():
    """[(shot, what it shows, where its numbers come from)], the twelve in the board's order."""
    out = []
    for name, shows, key, proposal in VIEWS:
        if key in ("V1", "V2"):
            view, source = proposal, "skeleton" if hasattr(S, "V2") else "A0 #304, not in the skeleton yet"
        elif hasattr(S, key):
            view, source = getattr(S, key), "skeleton"
        else:
            view, source = proposal, "PROPOSED"
        shot = dict(name=name, pos=[round(float(v), 2) for v in view["pos"]],
                    look_at=[round(float(v), 2) for v in view["look_at"]], time=TIME)
        out.append((shot, shows, source))
    return out


def text():
    """The file's text: one shot a line, so a change shows as one line in a diff."""
    return "[\n" + ",\n".join(" " + json.dumps(shot) for shot, _, _ in views()) + "\n]\n"


# ---- where things fall in a picture ---------------------------------------------------------------
def frame(shot):
    """Eye, forward, right, up of a shot, as the game and tools/sightline.py have them."""
    pos, to = shot["pos"], shot["look_at"]
    f = [to[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [f[1] * 0.0 - f[2] * 1.0, 0.0, f[0] * 1.0 - f[1] * 0.0]      # forward x up
    n = math.hypot(r[0], r[2])
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return pos, f, r, u


def falls(cam, direction):
    """(across, down) of a direction in the picture, each 0 .. 1 inside it; None behind the camera."""
    _, f, r, u = cam
    depth = sum(direction[i] * f[i] for i in range(3))
    if depth <= 1e-9:
        return None
    ty = math.tan(math.radians(FOV) / 2.0)
    return (0.5 + sum(direction[i] * r[i] for i in range(3)) / depth / (2.0 * ty * ASPECT),
            0.5 - sum(direction[i] * u[i] for i in range(3)) / depth / (2.0 * ty))


def landmarks():
    """Named points of the site, scene coordinates, from the skeleton."""
    front = S.WALL_E + S.DEPTH_PILASTER + 1.0
    mast = S.RADIO_MAST["foot"]
    small = (S.mid(*S.SMALL_DOME_X), S.mid(*S.SMALL_DOME_Z))
    points = [
        ("dome apex", (S.DOME_AXIS[0], S.DOME_APEX + 1.0, S.DOME_AXIS[1])),
        ("dome spring, north", (S.DOME_AXIS[0], S.DOME_SPRING, S.DOME_AXIS[1] - S.DOME_R)),
        ("dome spring, south", (S.DOME_AXIS[0], S.DOME_SPRING, S.DOME_AXIS[1] + S.DOME_R)),
        ("time-ball mast top", (TOWER[0], S.CLOCK_BALL_MAST + 1.0, TOWER[1])),
        ("tower shaft top", (TOWER[0], S.CLOCK_SHAFT_TOP + 1.0, TOWER[1])),
        ("small dome apex", (small[0], S.SMALL_DOME_APEX + 1.0, small[1])),
        ("radio mast top", (mast[0] + 0.5, S.GROUND + S.RADIO_MAST["height"], mast[1] + 0.5)),
        ("radio mast foot", (mast[0] + 0.5, S.GROUND, mast[1] + 0.5)),
        ("front, north end, parapet", (front, S.PARAPET[1] + 1.0, S.Z_NORTH)),
        ("front, south end, parapet", (front, S.PARAPET[1] + 1.0, S.Z_SOUTH + 1.0)),
        ("front, north end, foot", (front, S.GROUND, S.Z_NORTH)),
        ("front, south end, foot", (front, S.GROUND, S.Z_SOUTH + 1.0)),
        ("main door", (S.east_wall_x(9) + 1.0, 2.5, S.AXIS_Z)),
        ("armillary", (S.ARMILLARY[0] + 0.5, 2.0, S.ARMILLARY[1] + 0.5)),
        ("stair head", (S.EAST_EDGE_X + 1.0, S.GROUND, S.AXIS_Z)),
        ("stair foot", (S.GRAND_STAIR["x1"] + 1.0, S.LOWER_GROUND, S.AXIS_Z)),
        ("cable station, north-east", (S.CABLE_STATION[2] + 1.0, S.STATION_GROUND, S.CABLE_STATION[1])),
        ("cable station, south-west", (S.CABLE_STATION[0], S.STATION_GROUND, S.CABLE_STATION[3] + 1.0)),
        ("lower platform, south-east", (S.LOWER_PLATFORM[2] + 1.0, S.LOWER_GROUND, S.LOWER_PLATFORM[3] + 1.0)),
        ("power house, middle of the roof", (S.mid(HOUSE[0], HOUSE[2]), S.POWER_HOUSE["base_y"] + S.POWER_HOUSE["wall_h"],
                                             S.mid(HOUSE[1], HOUSE[3]))),
        ("over the power house, at the chimney's height", (S.mid(HOUSE[0], HOUSE[2]), S.POWER_HOUSE["base_y"] + S.POWER_HOUSE["chimney_h"],
                                         S.mid(HOUSE[1], HOUSE[3]))),
        ("meridian hut", (S.MERIDIAN_HUT["centre"][0] + 0.5, 4.0, S.MERIDIAN_HUT["centre"][1] + 0.5)),
        ("sunset platform, west edge", (S.SUNSET_PLATFORM["centre"][0] - S.SUNSET_PLATFORM["radius"], S.GROUND, S.AXIS_Z)),
    ]
    for name, shelf in (("water tower", S.WATER_TOWER), ("weather station", S.WEATHER_STATION),
                        ("south lookout", S.SOUTH_LOOKOUT), ("mast pad", S.MAST_PAD)):
        box = shelf["box"]
        points.append((name, (S.mid(box[0], box[2]), shelf["feet"], S.mid(box[1], box[3]))))
    points += [
        ("orrery", (S.ORRERY_CENTRE[0], S.ORRERY_RING_Y, S.ORRERY_CENTRE[1])),
        ("mother clock", (S.MOTHER_CLOCK["back_x"], 3.0, S.MOTHER_CLOCK["z"])),
        ("pier top", (S.DOME_AXIS[0], S.PIER_TOP_Y, S.DOME_AXIS[1])),
    ]
    return points


def explain():
    """For every view: its pitch, and where each landmark falls (across, down; 0 .. 1 is inside)."""
    marks = landmarks()
    for shot, shows, source in views():
        cam = frame(shot)
        pos, f = cam[0], cam[1]
        pitch = math.degrees(math.asin(f[1]))
        heading = math.degrees(math.atan2(f[0], -f[2])) % 360.0       # 0 north, 90 east
        print(f"{shot['name']}: {shows}")
        print(f"    {source}: pos {shot['pos']}, look_at {shot['look_at']}, "
              f"heading {heading:.0f} (0 north, 90 east), pitch {pitch:+.1f}")
        inside, far = [], []
        for name, p in marks:
            d = [p[i] - pos[i] for i in range(3)]
            at = falls(cam, d)
            if at is not None and 0.0 <= at[0] <= 1.0 and 0.0 <= at[1] <= 1.0:
                inside.append(f"{name} ({at[0]:.2f}, {at[1]:.2f})")
                if math.hypot(d[0], d[2]) > SERVER_SENDS:
                    far.append(f"{name} ({math.hypot(d[0], d[2]):.0f})")
        print("    in the picture: " + ("; ".join(inside) or "none of the landmarks"))
        if far:
            print(f"    further than {SERVER_SENDS:.0f} blocks on the ground, display entities there are not sent: "
                  + "; ".join(far))
        # the comet's head stands due west, 41 degrees up (c230, group #300)
        at = falls(cam, (-math.cos(math.radians(41.0)), math.sin(math.radians(41.0)), 0.0))
        if at is not None and 0.0 <= at[0] <= 1.0 and 0.0 <= at[1] <= 1.0:
            print(f"    the comet's head (due west, 41 up) falls at ({at[0]:.2f}, {at[1]:.2f}), if nothing hides it")


def main():
    ap = argparse.ArgumentParser(description="the twelve board views, from the skeleton")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.write or args.out:
        path = os.path.abspath(args.out or FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text())
        print(f"written: {path} ({len(VIEWS)} views; skeleton: {os.path.dirname(os.path.abspath(S.__file__))})")
        return 0
    if args.check:
        try:
            with open(FILE, encoding="utf-8") as fh:
                kept = json.load(fh)
        except (OSError, ValueError) as e:
            print(f"{FILE}: {e}")
            return 1
        now = [shot for shot, _, _ in views()]
        if kept != now:
            names = sorted({s["name"] for s in kept if s not in now} | {s["name"] for s in now if s not in kept})
            print("the kept list is not what the skeleton gives now (" + ", ".join(names)
                  + "): run tools/boardshots.py --write and commit")
            return 1
        print(f"the kept list is what the skeleton gives ({len(now)} views)")
        return 0
    explain()
    return 0


if __name__ == "__main__":
    sys.exit(main())
