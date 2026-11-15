"""Test scene of the work package machines/cablecar-winch (plan/packages/machines/cablecar-winch.md):
the cable car, its winch and the haul rope at the cable station.

The stage is the station itself, where it stands in the master scene. With site/cablecar in the
tree the scene builds that package's blocks; until then a stand-in of the same blocks (_station.py,
by the figures of its second draft), so that the machines are tried against the opening, the
girder, the rails and the glass roof they are made for. Round it, in this scene only and in empty
cells only: the corner of the lower platform, to stand on for the far view; the flank of the hill
east of it with the ridge under the trestle; a sheet of cloud for the track to go down into.

The pendant over the car's door is one of the site's lamps (props/lamps, its group "station"). It
is asked for here, so that the car is seen in the light it will stand in. The winch's wall lamp is
the machines' own (machines/cable.WORK_LAMP). The sky line's light sources go in last.

The views (shots(); python -m scenes.obs_mach_cablecar_winch writes them to shots.json):

  v1                        the arrival view as the skeleton fixes it: nothing of the machines is in it
  back                      the same eye turned round: the car's door
  door                      the car's door end from the head of the track, between the buffer stops
  car, car_side, car_end    the car from three blocks: from the platform, from the bay between the
                            glass roof's columns, from over the trestle
  winch                     the winch house's opening from across the platform
  winch_near, drum_east     the drum from the threshold, and along it from the east
  motor, sheave             the motor with its belt; the lead sheave, the rope going into the floor
  brow, track               the rope leaving the platform, and going down the trestle into the cloud
  far                       the station from the lower platform
"""
from artkit.canvas import Canvas, Mix

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import cable
from scenes.obs.props import lamps
from scenes.obs.site import _kit as K

from . import _station

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default

STATION = cable.SHELL if cable.SHELL is not None else _station       # who builds the station's blocks
STATION_LEVEL = 12              # the level props/lamps gives the station's pendant (its STATION_LEVEL)

LOWER = B.TUFF_BRICK.block      # the lower platform's paving (site/ground)
ROCK = Mix({B.TUFF.block: 5, B.ROCK_ANDESITE.block: 3, B.ROCK_COBBLED.block: 2, B.ROCK_DEEPSLATE: 3}, seed=240)
CLOUD = Mix({B.CLOUD[1]: 2, B.CLOUD[2]: 3, B.CLOUD[3]: 2}, seed=241)
CLOUD_Y = (-27, -26)            # the block cloud's two courses; its top face is at y -25
CORNER = (S.LOWER_PLATFORM[0], S.LOWER_PLATFORM[1], S.LOWER_PLATFORM[2], -8)    # x 61..91, z -42..-8: the lower
#                                                                                 platform's north-east corner
FLANK = (CORNER[2] + 1, -66, CORNER[2] + 15, -14)       # x 92..106: the hill's east flank, down to the rock floor
SEA = (86, -80, 160, -8)        # where the cloud is drawn

# --- the views --------------------------------------------------------------------------------------
STAND = S.STATION_GROUND + S.EYE        # -2.38: the eye of who stands on the station platform
# The arrival view is the skeleton's. It looks up at (8, 34, 0.5) since A0 #304; a tree whose
# skeleton does not carry that figure yet gets it here.
V1 = S.V1 if hasattr(S, "V1_CLEAR") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
VIEWS = [
    ("v1", V1["pos"], V1["look_at"]),
    # The same eye turned round. It stands a step off the skeleton's: a camera on that very point
    # is the arrival view's, and looks where the skeleton says.
    ("back", (V1["pos"][0] + 0.05, V1["pos"][1], V1["pos"][2]), (90.5, -2.55, -32.5)),
    ("door", (86.5, STAND, -32.5), (90.0, -2.6, -32.5)),
    # the car from three blocks: its door end and south side, its south side square on between the
    # two columns of the glass roof, its valley end from over the trestle
    ("car", (87.4, STAND, -29.4), (90.4, -2.7, -32.4)),
    ("car_side", (90.6, -2.3, -28.4), (90.5, -2.6, -32.5)),
    ("car_end", (94.6, -2.0, -31.2), (91.5, -2.7, -32.5)),
    # the winch: the whole opening under its girder from the bay's south end, the drum read along
    # its length between the two wheels rather than end on (cr3-M7 item 1: from the bay's west end
    # the drum, its wheels and the lever piled into one dark mass); the drum from the kerb north of
    # the car; along the drum from the opening's east corner
    ("winch", (88.5, STAND, -30.0), (89.0, -1.9, -37.4)),
    ("winch_near", (89.9, STAND, -34.5), (88.8, -2.6, -37.4)),
    ("drum_east", (90.9, -2.3, -34.4), (88.9, -2.5, -37.2)),
    ("motor", (87.1, -2.9, -34.5), (88.0, -3.3, -36.0)),
    ("sheave", (90.0, -3.0, -34.4), (89.25, -3.45, -35.6)),
    # the rope: off the platform, round the level roller and over the brow; down the trestle
    ("brow", (93.8, -2.9, -31.0), (93.9, -3.8, -33.3)),
    ("track", (92.3, -2.0, -30.6), (106.0, -10.0, -37.0)),
    ("far", (79.5, S.LOWER_GROUND + S.EYE, -14.5), (88.0, -2.4, -33.5)),
]


def shots(names=None):
    """The shot list, or the views of it that are named."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS if names is None or name in names]


# --- the stage --------------------------------------------------------------------------------------
def _crust(c, x, z, top, thick=3):
    for y in range(top, max(top - thick, K.ROCK_FLOOR) - 1, -1):
        c.set(x, y, z, ROCK, keep=True)


def _hill(c):
    """What the station stands on and looks out over, as far as these views see it. Stand-ins for
    site/terrain's east flank and for sky/cloudsea; they fill empty cells only."""
    x0, z0, x1, z1 = CORNER
    c.box(x0, S.LOWER_PAVING_Y, z0, x1, S.LOWER_PAVING_Y, z1, LOWER, keep=True)
    for x in range(FLANK[0], FLANK[2] + 1):             # the slope below the lower platform's east edge
        for z in range(FLANK[1], FLANK[3] + 1):
            d = max(x - x1, z0 - z)
            top = int(round(S.LOWER_PAVING_Y - 1 - 1.6 * (d - 1)))
            if top >= K.ROCK_FLOOR:
                _crust(c, x, z, top)
    for x in range(K.CABLE_RIDGE_X[0], K.CABLE_RIDGE_X[1] + 1):     # the ridge, falling two in one each side
        z, y = K.cable_ridge(x)
        for k in range(0, 14):
            top = y - 2 * max(0, k - 1)
            if top < K.ROCK_FLOOR:
                break
            for zz in {z - k, z + k}:
                _crust(c, x, zz, top)
    for x in range(SEA[0], SEA[2] + 1):
        for z in range(SEA[1], SEA[3] + 1):
            for y in CLOUD_Y:
                c.set(x, y, z, CLOUD, keep=True)


def _station_lamp(c):
    """The pendant under the glass roof, over the car's door. props/lamps hangs it from
    site/cablecar's hanging point once both are in the tree; until then it is hung here, on the
    same point and at the same level. Returns the display entities placed."""
    hang = getattr(lamps, "site", None)
    if hang is not None and cable.SHELL is not None:
        return hang(c, (0, 0, 0), groups=("station",))
    return lamps.place(c, "pendant", STATION.LAMP_POINTS["car"], level=STATION_LEVEL)


def build():
    c = Canvas()
    STATION.build(c, (0, 0, 0))
    _hill(c)
    n = cable.build(c, (0, 0, 0))
    hung = _station_lamp(c)
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"machines": n, "props": hung}
    return c


def write_pack(pack_dir):
    """The machines paint their own models; the stage stands on the repainted blocks as the
    materials line has them (tuff, cast iron, the roof light, the lit and dark windows)."""
    return materials.pack(pack_dir)
