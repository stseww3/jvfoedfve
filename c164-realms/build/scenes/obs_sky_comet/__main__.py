"""python -m scenes.obs_sky_comet (in build/): write shots.json, print where the comet stands."""
import os

from . import STYLE, tell

tell(STYLE, os.path.dirname(os.path.abspath(__file__)))
