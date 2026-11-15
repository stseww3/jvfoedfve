"""python -m scenes.obs_sky_ridges (in build/): write shots.json, print what every shot holds."""
import os

from . import tell

tell(os.path.dirname(os.path.abspath(__file__)))
