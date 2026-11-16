"""obs_int_timeroom_master: a look only, on throwaway branches and never delivered. The master
scene exactly as this tree builds it, shot from inside the time room: has the room moved in, and
what do V10 and the board's present place for V10 show of it.
"""
from scenes import obs

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y
CATEGORY = "interiors"


def build():
    return obs.build()


def write_pack(pack_dir):
    return obs.write_pack(pack_dir)
