"""obs_int_clockroom without the clock room: the same shell, the tower shut and its well empty, seen
by the same two cameras from outside under the same names. Its pictures lie beside the base
scene's ext_v5 and ext_v1: the tower must look the same and be as bright with the room in it.
shots.json of both is written by  python -m scenes.obs_int_clockroom.
"""
from scenes import obs_int_clockroom as base
from scenes.obs_int_clockroom import BIOME, CATEGORY, TIME, build_models, write_pack  # noqa: F401

OUTSIDE = ("ext_v5", "ext_v1")


def shots():
    return [row for row in base.shots() if row["name"] in OUTSIDE]


def build():
    return base.build(room_in=False)
