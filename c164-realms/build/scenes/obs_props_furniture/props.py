"""The models of the props/furniture test scene, and how gallery.py lays them out one to a bay."""
from scenes.obs.props import furniture, instruments, lamps

SCALE = {**lamps.SCALE, **instruments.SCALE, **furniture.SCALE}
P = furniture.PREFIX


def build_models():
    """The furniture, the lamps that light the stage and the instruments that give the scale."""
    return {**lamps.models(), **instruments.models(), **furniture.models()}


def _floor(name, height=1.0):
    return (name, [(P + name, None, {})], (1.6, height + 0.8, 3.0), (0.0, height * 0.5, 0.0))


def _wall(name, y):
    """A piece that leans on or hangs from the backdrop wall, its anchor y blocks up."""
    return (name, [(P + name, (0.0, y, -7.49), {})], (1.8, 1.6, -3.0), (0.0, 1.4, -7.2))


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    _floor("bench"), _floor("writing_desk"), _floor("drafting_table", 1.5), _floor("swivel_chair"),
    _floor("stool"), _floor("card_cabinet", 2.0), _floor("instrument_cabinet", 2.0), _wall("library_ladder", 0.0),
    _wall("ladder_rail", furniture.RAIL_Y), _floor("coat_stand", 2.0), _floor("trunk"), _floor("crate"),
    _floor("crate_small"), _floor("display_case", 1.4), _floor("display_table"),
    _floor("plate_box"), _floor("display_table_plates"), _floor("display_table_lenses"),
]
