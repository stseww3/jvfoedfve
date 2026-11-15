"""A bench for main/dome while it is being polished: obs_main_dome with constants of main/_dome.py
set from the environment, so that several ways of laying the dome can be drawn in one job and
looked at side by side. Not a test scene of the package and not kept: it goes when the dome is
delivered.

    DOME_LAB="version=b;LIP=();HEM=1" python build/render.py obs_main_dome_lab --shots ... --out ...
"""
import os

from scenes import obs_main_dome as base
from scenes.obs_main_dome import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401
from scenes.obs.main import _dome as D


def build():
    version, slit = "a", None
    for item in filter(None, os.environ.get("DOME_LAB", "").split(";")):
        key, _, value = item.partition("=")
        if key == "version":
            version = value
        elif key == "slit":
            slit = value
        else:
            setattr(D, key, eval(value))
    D.meridians.cache_clear()
    return base.build(version, slit)
