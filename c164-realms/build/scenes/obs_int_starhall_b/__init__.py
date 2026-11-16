"""obs_int_starhall with the hall in version b, "workshop". Everything else is the same scene:
the same shell, machines and lights, the same cameras under the same names (shots.json of both is
written by  python -m scenes.obs_int_starhall).
"""
from scenes import obs_int_starhall as base
from scenes.obs_int_starhall import BIOME, BIOME_MARGIN, build_models, write_pack  # noqa: F401

VERSION = "b"


def build():
    return base.build(VERSION)
