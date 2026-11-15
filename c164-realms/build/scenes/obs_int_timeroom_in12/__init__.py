"""obs_int_timeroom_in12: obs_int_timeroom_in with the sources behind the wings' lit windows at 12
(the director's ruling of 11-16 05:00). A look only, on the preview branch and never delivered."""
from scenes import obs_int_timeroom_in as base

BIOME = base.BIOME
BIOME_MARGIN = base.BIOME_MARGIN
CATEGORY = base.CATEGORY
BEHIND = 12


def build():
    return base.build(BEHIND)


def write_pack(pack_dir):
    return base.write_pack(pack_dir)
