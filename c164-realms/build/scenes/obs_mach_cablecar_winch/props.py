"""The models of the machines/cablecar-winch test scene, and how gallery.py lays them out one to a
bay: the machines' own, and the two of the lamp family that hang in the scene (the winch's wall
lamp, the station's pendant over the car's door)."""
from scenes.obs.machines import cable
from scenes.obs.props import lamps

P = cable.PREFIX
LAMPS = [lamps.PREFIX + (f"{kind}_{lamps.VERSION}" if kind in lamps.VERSIONED else kind)
         for kind in (cable.LAMP_KIND, "pendant")]
SCALE = dict(cable.SCALE)
SCALE.update({name: lamps.SCALE[name] for name in LAMPS})


def build_models():
    out = cable.models()
    family = lamps.models()
    out.update({name: family[name] for name in LAMPS})
    return out


def _floor(name, cam=(1.6, 1.3, 2.2), look=(0.0, 0.4, 0.0)):
    return (name, [(P + name, None, {})], cam, look)


_AXLE = (0.0, cable.AXLE[1] - cable.FEET, 0.0)          # the drum and its frame stand on one point, the axle
_PIN = (0.0, cable.SHEAVE[1] - cable.FEET, 0.0)         # so do the lead sheave and its stand

# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    ("car", [(P + "car", None, {})], (3.4, 1.9, 3.8), (0.0, 1.4, 0.0)),
    ("winch", [(P + "drum", _AXLE, {}), (P + "frame", _AXLE, {})], (3.6, 2.2, 4.6), (0.0, 1.5, 0.0)),
    _floor("motor"),
    ("sheave", [(P + "sheave", _PIN, {}), (P + "stand", _PIN, {})], (1.5, 1.2, 1.9), (0.0, 0.5, 0.0)),
    _floor("hood"), _floor("duct"), _floor("turn"), _floor("roller"),
    ("rope", [(P + "rope", (0.0, 0.5, -1.5), {}), (P + "belt", (0.6, 0.5, -1.5), {})], (1.6, 1.2, 1.8), (0.3, 0.5, 0.0)),
]
