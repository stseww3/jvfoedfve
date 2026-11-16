"""Test scene of the work package machines/cablecar-winch (plan/packages/machines/cablecar-winch.md):
the cable car, its winch and the haul rope at the cable station.

The stage is the station where it stands in the master scene, on the hill as the assembly has it:
the site line whole (the station is site/cablecar's), the main building above it, the machines
line (the car and the winch are its package machines/cable), the props line (the pendant over the
car's door, the station's name board) and the sky line's light last. The lines are built whole, in
the master scene's order, so the pictures keep up with them as their packages are merged. The
station's furniture, which the props line keeps for a canvas that asks, is asked for here.

The views (shots(); python -m scenes.obs_mach_cablecar_winch writes them to shots.json):

  v1                        the arrival view as the skeleton fixes it: nothing of the machines is in it
  back                      the same eye turned round: the car's door
  door                      the car's door end from the head of the track, between the buffer stops
  car, car_side, car_end    the car from three blocks: from the platform, from the bay between the
                            glass roof's columns, from over the trestle
  winch                     the winch house's opening from across the platform, the winch's rail before it
  winch_near                the drum from where one stands at the rail
  drum_east, motor, sheave  from behind the rail, where nobody stands, to read the pieces: along the
                            drum from the east; the motor with its belt; the lead sheave, the rope
                            going into the floor
  brow, track               the rope leaving the platform, and going down the trestle into the cloud
  far                       the station from the lower platform
"""
import importlib

from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.machines import cable
from scenes.obs.site import cablecar

BIOME = "obs_blue"
CATEGORY = "machines"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
TIME = 14000                    # light version A, the default
LINES = (site, main, machines, props, sky)

# --- the views --------------------------------------------------------------------------------------
STAND = S.STATION_GROUND + S.EYE        # -2.38: the eye of who stands on the station platform
V1 = S.V1
CAR_X, _, CAR_Z = cable.CAR             # the middle of the car's foot: (91.0, -32.5)
VIEWS = [
    ("v1", V1["pos"], V1["look_at"]),
    # The same eye turned round. It stands a step off the skeleton's: a camera on that very point
    # is the arrival view's, and looks where the skeleton says.
    ("back", (V1["pos"][0] + 0.05, V1["pos"][1], V1["pos"][2]), (CAR_X, -2.55, CAR_Z)),
    ("door", (86.5, STAND, -32.5), (CAR_X - 1.0, -2.6, CAR_Z)),
    # the car from three blocks: its door end and south side, its south side square on between the
    # two columns of the glass roof, its valley end from over the trestle
    ("car", (87.4, STAND, -29.4), (CAR_X - 0.3, -2.7, CAR_Z)),
    ("car_side", (90.5, -2.3, -28.4), (CAR_X - 0.1, -2.6, CAR_Z)),
    ("car_end", (95.4, -2.0, -30.6), (CAR_X + 1.0, -2.7, CAR_Z)),
    # the winch: the whole opening under its girder, its rail before it, from the bay's west end;
    # the drum from where one stands at the rail. Then three from behind the rail, where nobody
    # stands, to read the pieces: along the drum from the opening's east corner, the motor, the sheave
    ("winch", (87.0, STAND, -30.0), (89.0, -1.9, -37.4)),
    ("winch_near", (89.6, STAND, -34.1), (88.8, -2.6, -37.4)),
    ("drum_east", (90.9, -2.3, -34.9), (88.9, -2.5, -37.2)),
    ("motor", (87.25, -2.9, -34.95), (88.0, -3.3, -36.0)),
    ("sheave", (90.7, -3.0, -34.9), (cable.SHEAVE[0], -3.45, cable.SHEAVE[2])),
    # the rope: off the platform, round the level roller and over the brow; down the trestle
    ("brow", (94.3, -2.9, -31.0), (94.0, -3.8, -33.3)),
    ("track", (92.6, -2.0, -30.4), (106.0, -10.0, -37.0)),
    ("far", (79.5, S.LOWER_GROUND + S.EYE, -14.5), (88.0, -2.4, -33.5)),
]


def shots(names=None):
    """The shot list, or the views of it that are named."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS if names is None or name in names]


# --- the stage --------------------------------------------------------------------------------------
def _prop(name):
    """A package of the props line; None while it is not in the tree."""
    full = f"{props.__name__}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise               # it is there and fails to import something: say so
        return None


def _dress(c):
    """The two benches and the luggage against the waiting room (props/furniture, its group
    "station"): a piece that stands already is not set out twice."""
    set_out = getattr(_prop("furniture"), "site", None)
    if set_out is not None:
        set_out(c, (0, 0, 0), groups=("station",))


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
        if line is site:
            cablecar.lining(c)      # the materials line is not built here: the room side of the winch
            #                         house's two lights, behind the winch
        if line is props:
            _dress(c)
    return c


def build_models():
    """The models of the lines that are built here, and the materials line's (the sheets of
    cablecar.lining are its models)."""
    out = {}
    for line in (materials,) + LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The machines paint their own models; the stage stands on the repainted blocks as the
    materials line has them, under the map's sky: the scene keeps the map's hour (mood.py)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
