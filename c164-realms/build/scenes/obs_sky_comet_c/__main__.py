"""python -m scenes.obs_sky_comet_c (in build/): write shots.json, print where the comet stands."""
import os

from . import STYLE, shots, tell

tell(STYLE, os.path.dirname(os.path.abspath(__file__)), shots)
